

public class Benchmark8 {
    public static void main(String[] args) {
        // fetch input
        Integer input_1_0 = Integer.valueOf(args[0]);
        Integer input_2_0 = Integer.valueOf(args[1]);


        // Perform computation         
        Byte output_1 = Character.getDirectionality(input_1_0);
        Byte output_2 = Character.getDirectionality(input_2_0);

        
        // Compare output
        if (output_1 == 9 && output_2 == -1) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

