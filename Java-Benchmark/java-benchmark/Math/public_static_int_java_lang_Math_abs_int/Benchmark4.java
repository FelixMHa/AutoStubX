

public class Benchmark4 {
    public static void main(String[] args) {
        // fetch input
        Integer input_1_0 = Integer.valueOf(args[0]);
        Integer input_2_0 = Integer.valueOf(args[1]);


        // Perform computation         
        Integer output_1 = Math.abs(input_1_0);
        Integer output_2 = Math.abs(input_2_0);

        
        // Compare output
        if (output_1 == 195440991 && output_2 == 13815828) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

