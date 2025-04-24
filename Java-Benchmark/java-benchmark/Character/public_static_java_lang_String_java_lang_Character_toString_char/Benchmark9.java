

public class Benchmark9 {
    public static void main(String[] args) {
        // fetch input
        Character input_1_0 = args[0].charAt(0);
        Character input_2_0 = args[1].charAt(0);


        // Perform computation         
        String output_1 = Character.toString(input_1_0);
        String output_2 = Character.toString(input_2_0);

        
        // Compare output
        if (output_1.equals("`") && output_2.equals("6")) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

